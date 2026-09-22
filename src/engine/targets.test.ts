import { describe, expect, it } from "vitest";
import { targetsProgram } from "./targets";
import { recommend } from "./recommend";
import { unlockStatus } from "./unlockStatus";
import type { Card, CardHistoryEntry, Currency, EngineData, Household, Player, Profile, Program } from "./types";
import cardsJson from "../../data/cards.json";
import currenciesJson from "../../data/currencies.json";
import programsJson from "../../data/programs.json";

const catalog = cardsJson as unknown as Card[];
const currencies = currenciesJson as unknown as Currency[];
const programs = programsJson as unknown as Program[];
const real = new Map(catalog.map((c) => [c.id, c]));
const held = (): CardHistoryEntry => ({ current: 1, approved: { gt48: 1 } });
const person = (cards: Record<string, CardHistoryEntry> = {}, name = "P1"): Player => ({
  name, history: { cards }, shutdownIssuers: [], bannedFromAA: false, openToBusinessCards: true, wantsUnder524: false,
});
const house = (targetPrograms: string[], excludedPrograms: string[] = []): Household => ({
  maxAnnualFee: null, spend3Months: 1e9, spend6Months: 1e9, supplementalSpend3Months: 0, bonusTypes: [], excludedPrograms, targetPrograms,
});
const targets = (id: string, targetList: string[], p = person(), excluded: string[] = []) =>
  targetsProgram(p, real.get(id)!, { household: house(targetList, excluded), currencies, programs, unlock: unlockStatus([p], currencies).get(p.name)! });

describe("targetsProgram", () => {
  it("is false when nothing is targeted", () => {
    expect(targets("amex-delta-gold", [])).toBe(false);
  });
  it("is true for a co-branded card whose program is targeted", () => {
    expect(targets("amex-delta-gold", ["delta-skymiles"])).toBe(true);
    expect(targets("amex-delta-gold", ["united-mileageplus"])).toBe(false);
  });
  it("matches a program group, such as Avios, by group or by id", () => {
    expect(targets("chase-british-airways", ["Avios"])).toBe(true);
    expect(targets("chase-british-airways", ["avios"])).toBe(true);
  });
  it("counts a transferable card that leads to the program once the currency is unlocked", () => {
    expect(targets("chase-freedom-flex", ["world-of-hyatt"])).toBe(false);
    expect(targets("chase-freedom-flex", ["world-of-hyatt"], person({ "chase-sapphire-preferred": held() }))).toBe(true);
  });
  it("counts an unlocker card itself, since getting it unlocks the currency", () => {
    expect(targets("chase-sapphire-preferred", ["world-of-hyatt"])).toBe(true);
  });
  it("does not count a partner the currency does not reach", () => {
    expect(targets("chase-sapphire-preferred", ["delta-skymiles"])).toBe(false);
  });
  it("is false for a program that is also excluded", () => {
    expect(targets("chase-sapphire-preferred", ["world-of-hyatt"], person(), ["world-of-hyatt"])).toBe(false);
  });
  it("is false for cash cards", () => {
    expect(targets("amex-blue-business-cash", ["delta-skymiles"])).toBe(false);
  });
});

describe("recommend: targeted programs rank first", () => {
  const P: Program[] = [{ id: "delta", name: "Delta", kind: "airline" }];
  const mk = (id: string, value: number, extra: Partial<Card> = {}): Card => ({
    id, name: id, issuer: "citi", kind: "personal", recommendable: true, annualFee: 0, reportsToPersonal: true,
    currency: "cash", bonusTypes: ["cashback"], welcomeBonus: { cashBack: value }, verifiedOn: "2026-01-01", ...extra,
  });
  const delta = (id: string, value: number) => mk(id, value, { currency: undefined, bonusTypes: ["airline"], coBrandedProgram: "delta" });
  const data = (catalog: Card[]): EngineData => ({
    catalog, currencies: [], programs: P, valuations: { values: {}, freeNightCertificates: {} }, marriottMatrix: { rules: {}, matrix: {} },
  });
  const profile = (players: Player[], targetPrograms: string[]): Profile => ({ version: 1, players, household: house(targetPrograms) });
  const ids = (p: Profile, c: Card[], perPlayer = 5) => recommend(p, data(c), { perPlayer }).ranked.map((e) => e.cardId);

  it("puts cards that lead to a targeted program above objectively better ones, then ranks by value", () => {
    const c = [mk("best", 900), delta("d-low", 100), mk("mid", 500), delta("d-high", 300)];
    expect(ids(profile([person()], ["delta"]), c)).toEqual(["d-high", "d-low", "best", "mid"]);
  });
  it("fills a player's top cards with targeted cards first", () => {
    const c = [mk("best", 900), delta("d-low", 100)];
    expect(ids(profile([person()], ["delta"]), c, 1)).toEqual(["d-low"]);
  });
  it("ranks the combined list with targeted cards first", () => {
    const c = [mk("best", 900), delta("d-low", 100)];
    expect(ids(profile([person(), person({}, "P2")], ["delta"]), c, 1)).toEqual(["d-low"]);
  });
  it("changes nothing when no program is targeted", () => {
    const c = [mk("best", 900), delta("d-low", 100), mk("mid", 500)];
    expect(ids(profile([person()], []), c)).toEqual(["best", "mid", "d-low"]);
  });
});
