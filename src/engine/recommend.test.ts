import { describe, expect, it } from "vitest";
import Ajv2020 from "ajv/dist/2020";
import { recommend } from "./recommend";
import type { Card, CardHistoryEntry, Currency, EngineData, Household, Player, Profile, Results } from "./types";
import cardsJson from "../../data/cards.json";
import currenciesJson from "../../data/currencies.json";
import programsJson from "../../data/programs.json";
import valuationsJson from "../../data/valuations.json";
import matrixJson from "../../data/marriott-matrix.json";
import resultsSchema from "../../data/schema/results.schema.json";

const flatValuations = { values: { twoRate: { withUnlocker: 1.5, withoutUnlocker: 1 } }, freeNightCertificates: {} };
const noMatrix = { rules: {}, matrix: {} };

/** A synthetic cash card worth `value` dollars (bonus minus fee). */
const mk = (id: string, value: number, extra: Partial<Card> = {}): Card => ({
  id, name: id, issuer: "citi", kind: "personal", recommendable: true, annualFee: 0, reportsToPersonal: true,
  currency: "cash", bonusTypes: ["cashback"], welcomeBonus: { cashBack: value }, verifiedOn: "2026-01-01", ...extra,
});
const ceiling = (id: string, value: number, extra: Partial<Card> = {}) => mk(id, value, { welcomeBonus: { cashBack: value, ceiling: true }, ...extra });

const person = (name = "P1", extra: Partial<Player> = {}, cards: Record<string, CardHistoryEntry> = {}): Player => ({
  name, history: { cards }, shutdownIssuers: [], bannedFromAA: false, openToBusinessCards: true, wantsUnder524: false, ...extra,
});
const household = (extra: Partial<Household> = {}): Household => ({
  maxAnnualFee: 100000, spend3Months: 1e9, spend6Months: 1e9, supplementalSpend3Months: 0, bonusTypes: [], excludedPrograms: [], ...extra,
});
const data = (catalog: Card[], currencies: Currency[] = []): EngineData => ({
  catalog, currencies, programs: [], valuations: flatValuations, marriottMatrix: noMatrix,
});
const profile = (players: Player[], h: Partial<Household> = {}): Profile => ({ version: 1, players, household: household(h) });
const ids = (r: Results) => r.ranked.map((e) => e.cardId);

describe("recommend: one player", () => {
  const cards = ["a", "b", "c", "d", "e", "f", "g", "h"].map((id, i) => mk(id, 800 - i * 100));

  it("lists the top 5 eligible cards by net value, best first", () => {
    expect(ids(recommend(profile([person()]), data(cards)))).toEqual(["a", "b", "c", "d", "e"]);
  });

  it("ranks on the bonus minus the annual fee", () => {
    const c = [mk("big-fee", 1000, { annualFee: 950 }), mk("small", 100), mk("mid", 60)];
    expect(ids(recommend(profile([person()]), data(c)))).toEqual(["small", "mid", "big-fee"]);
  });

  it("ranks a card with a waived first-year fee as if it had no fee", () => {
    const c = [mk("waived", 550, { annualFee: 95, firstYearFeeWaived: true }), mk("paid", 600, { annualFee: 95 })];
    // waived: 550 - 0; paid: 600 - 95 = 505
    expect(ids(recommend(profile([person()]), data(c)))).toEqual(["waived", "paid"]);
  });

  it("lists a different number per player when asked", () => {
    expect(ids(recommend(profile([person()]), data(cards), { perPlayer: 2 }))).toEqual(["a", "b"]);
  });

  it("skips cards the player cannot apply for, without counting them against the 5", () => {
    const shut = person("P1", { shutdownIssuers: ["citi"] });
    const mixed = [mk("c1", 900), mk("x1", 800, { issuer: "chase" }), mk("x2", 700, { issuer: "chase" })];
    expect(ids(recommend(profile([shut]), data(mixed)))).toEqual(["x1", "x2"]);
  });

  it("returns the player's standing", () => {
    const hist = person("P1", {}, { h1: { approved: { lt12: 2 } } });
    const r = recommend(profile([hist]), data([...cards, mk("h1", 0, { recommendable: false })]));
    expect(r.players).toEqual([{ name: "P1", x24: 2, overFiveTwentyFour: false, amexCredit: 0, amexCharge: 0, chaseBusinessOpen: 0 }]);
  });

  it("carries the fee, the minimum spend, the waived first year and the ceiling flag into each entry", () => {
    const c = [ceiling("a", 500, { annualFee: 95, firstYearFeeWaived: true, typicalMinSpend: { amount: 3000, months: 3 } })];
    expect(recommend(profile([person()]), data(c)).ranked[0]).toEqual({
      cardId: "a", players: [{ name: "P1" }], annualFee: 95, firstYearFeeWaived: true, minSpend: { amount: 3000, months: 3 }, ceiling: true,
      bonusValue: 500, netValue: 500,
    });
  });

  it("does not change its input and gives the same answer twice", () => {
    const p = profile([person()]);
    const d = data(cards);
    const before = JSON.stringify([p, d]);
    const first = recommend(p, d);
    expect(JSON.stringify([p, d])).toBe(before);
    expect(recommend(p, d)).toEqual(first);
  });
});

describe("recommend: raw or net value", () => {
  // big: bonus 900 with a $500 fee (net 400). small: bonus 600 with no fee (net 600).
  const cards = [mk("big", 900, { annualFee: 500 }), mk("small", 600)];

  it("ranks by net value, bonus minus the first-year fee, by default", () => {
    expect(ids(recommend(profile([person()]), data(cards)))).toEqual(["small", "big"]);
    expect(ids(recommend(profile([person()]), data(cards), { rankBy: "net" }))).toEqual(["small", "big"]);
  });
  it("ranks by raw bonus value, ignoring the fee, when asked", () => {
    expect(ids(recommend(profile([person()]), data(cards), { rankBy: "raw" }))).toEqual(["big", "small"]);
  });
  it("picks each player's top cards by the chosen value", () => {
    expect(ids(recommend(profile([person()]), data(cards), { rankBy: "net", perPlayer: 1 }))).toEqual(["small"]);
    expect(ids(recommend(profile([person()]), data(cards), { rankBy: "raw", perPlayer: 1 }))).toEqual(["big"]);
  });
  it("puts both values on every entry, whichever way the list is ranked", () => {
    for (const rankBy of ["net", "raw"] as const) {
      const r = recommend(profile([person()]), data(cards), { rankBy });
      const big = r.ranked.find((e) => e.cardId === "big")!;
      expect([big.bonusValue, big.netValue]).toEqual([900, 400]);
    }
  });
  it("counts a waived first-year fee as $0 in the net value", () => {
    const r = recommend(profile([person()]), data([mk("w", 300, { annualFee: 95, firstYearFeeWaived: true })]));
    expect([r.ranked[0]!.bonusValue, r.ranked[0]!.netValue]).toEqual([300, 300]);
  });
  it("uses the chosen value for the backups too", () => {
    const c = [ceiling("a", 900), mk("hi-fee", 800, { annualFee: 700 }), mk("no-fee", 300)];
    // net: a 900, no-fee 300, hi-fee 100. Top 1 is a (a ceiling), so the backup is the best remaining by the chosen value.
    expect(ids(recommend(profile([person()]), data(c), { perPlayer: 1, rankBy: "net" }))).toEqual(["a", "no-fee"]);
    expect(ids(recommend(profile([person()]), data(c), { perPlayer: 1, rankBy: "raw" }))).toEqual(["a", "hi-fee"]);
  });
});

describe("recommend: backups for 'as high as' offers", () => {
  it("adds one non-ceiling card below the top 5 for each ceiling card shown", () => {
    const c = [ceiling("a", 900), mk("b", 800), ceiling("c", 700), mk("d", 600), mk("e", 500), ceiling("f", 400), mk("g", 300), mk("h", 200), mk("i", 100)];
    const r = recommend(profile([person()]), data(c));
    expect(ids(r)).toEqual(["a", "b", "c", "d", "e", "g", "h"]); // two ceilings in the top 5, so two backups; f is a ceiling and skipped
    expect(r.ranked.filter((e) => e.players[0]!.backup).map((e) => e.cardId)).toEqual(["g", "h"]);
    expect(r.ranked.find((e) => e.cardId === "a")!.players[0]!.backup).toBeUndefined();
  });

  it("adds none when no ceiling card is shown", () => {
    const c = ["a", "b", "c", "d", "e", "f"].map((id, i) => mk(id, 600 - i * 100));
    expect(recommend(profile([person()]), data(c)).ranked.some((e) => e.players[0]!.backup)).toBe(false);
  });

  it("adds fewer when there are not enough suitable cards", () => {
    const c = [ceiling("a", 900), ceiling("b", 800), mk("c", 700), mk("d", 600), mk("e", 500), mk("f", 400)];
    expect(ids(recommend(profile([person()]), data(c)))).toEqual(["a", "b", "c", "d", "e", "f"]);
  });

  it("never picks a card that is only available through an NLL offer", () => {
    const lifetime = { onceInLifetime: true };
    const c = [ceiling("a", 900), mk("b", 800), mk("c", 700), mk("d", 600), mk("e", 500),
               mk("amex-nll", 400, { issuer: "amex", bonusRules: lifetime }), mk("g", 300)];
    const p = person("P1", {}, { "amex-nll": { approved: { gt48: 1 } } });
    expect(ids(recommend(profile([p]), data(c)))).toEqual(["a", "b", "c", "d", "e", "g"]);
  });
});

describe("recommend: NLL cards", () => {
  it("lists a card blocked only by Amex lifetime language at its rank, marked for that player", () => {
    const c = [mk("amex-a", 900, { issuer: "amex", bonusRules: { onceInLifetime: true } }), mk("b", 800)];
    const p = person("P1", {}, { "amex-a": { approved: { gt48: 1 } } });
    const r = recommend(profile([p]), data(c));
    expect(ids(r)).toEqual(["amex-a", "b"]);
    expect(r.ranked[0]!.players).toEqual([{ name: "P1", viaNllOnly: true }]);
  });

  it("marks NLL per player: one player needs an NLL offer and the other does not", () => {
    const c = [mk("amex-a", 900, { issuer: "amex", bonusRules: { onceInLifetime: true } })];
    const had = person("P1", {}, { "amex-a": { approved: { gt48: 1 } } });
    const r = recommend(profile([had, person("P2")]), data(c));
    expect(r.ranked[0]!.players).toEqual([{ name: "P1", viaNllOnly: true }, { name: "P2" }]);
  });
});

describe("recommend: several players", () => {
  it("merges the lists, labelling each card with the players who can apply", () => {
    const c = [mk("c1", 900), mk("x1", 800, { issuer: "chase" }), mk("c2", 700)];
    const p2 = person("P2", { shutdownIssuers: ["chase"] });
    const r = recommend(profile([person("P1"), p2]), data(c));
    expect(ids(r)).toEqual(["c1", "x1", "c2"]);
    expect(r.ranked.find((e) => e.cardId === "x1")!.players).toEqual([{ name: "P1" }]);
    expect(r.ranked.find((e) => e.cardId === "c1")!.players).toEqual([{ name: "P1" }, { name: "P2" }]);
  });

  it("combines each player's top cards and ranks the whole list by value", () => {
    // P1 cannot get Chase cards: P1's list is z, y. P2's top 3 is x1, w, z. The union, by value: x1, w, z, y.
    const c = [mk("x1", 900, { issuer: "chase" }), mk("w", 850, { issuer: "chase" }), mk("z", 800), mk("y", 100)];
    const r = recommend(profile([person("P1", { shutdownIssuers: ["chase"] }), person("P2")]), data(c), { perPlayer: 3 });
    expect(ids(r)).toEqual(["x1", "w", "z", "y"]);
    expect(r.ranked.find((e) => e.cardId === "z")!.players).toEqual([{ name: "P1" }, { name: "P2" }]);
    expect(r.ranked.find((e) => e.cardId === "w")!.players).toEqual([{ name: "P2" }]);
  });

  it("ranks a card shared by players at the highest value any of them gets from it", () => {
    const currency: Currency = { id: "twoRate", unlockerCards: ["unlocker"], householdPooling: false, partners: [], cashBackRedemption: "good" };
    const cards = [
      mk("lesser", 0, { currency: "twoRate", bonusTypes: ["transferable", "cashback"], welcomeBonus: { points: 100000 } }),
      mk("flat", 1200),
      mk("unlocker", 0, { currency: "twoRate", bonusTypes: ["transferable", "cashback"], welcomeBonus: { points: 60000 } }),
    ];
    const withUnlocker = person("P1", {}, { unlocker: { current: 1, approved: { gt48: 1 } } });
    // P1: lesser 1500; P2: lesser 1000. flat is 1200 for both. Combined by the highest value: lesser, flat, unlocker.
    const r = recommend(profile([withUnlocker, person("P2")]), data(cards, [currency]), { perPlayer: 3 });
    expect(ids(r)).toEqual(["lesser", "flat", "unlocker"]);
  });

  it("breaks value ties by card id", () => {
    const c = [mk("b", 500), mk("a", 500), mk("c", 500)];
    expect(ids(recommend(profile([person("P1"), person("P2")]), data(c)))).toEqual(["a", "b", "c"]);
  });

  it("puts a backup where its value places it, even above another player's main card", () => {
    // P1 (no Chase) has a (a ceiling, 900) and its backup b (700). P2 (no Citi) has only m (300). By value: a, b, m.
    const c = [ceiling("a", 900), mk("b", 700), mk("m", 300, { issuer: "chase" })];
    const players = [person("P1", { shutdownIssuers: ["chase"] }), person("P2", { shutdownIssuers: ["citi"] })];
    const r = recommend(profile(players), data(c), { perPlayer: 1 });
    expect(ids(r)).toEqual(["a", "b", "m"]);
    expect(r.ranked.find((e) => e.cardId === "b")!.players).toEqual([{ name: "P1", backup: true }]);
  });
});

describe("recommend: unlocking currencies change the value", () => {
  const currency: Currency = { id: "twoRate", unlockerCards: ["unlocker"], householdPooling: false, partners: [], cashBackRedemption: "good" };
  const cards = [
    mk("lesser", 0, { currency: "twoRate", bonusTypes: ["transferable", "cashback"], welcomeBonus: { points: 100000 } }),
    mk("flat", 1200),
    mk("unlocker", 0, { currency: "twoRate", bonusTypes: ["transferable", "cashback"], welcomeBonus: { points: 60000 }, annualFee: 0 }),
  ];

  it("values a card at the without-unlocker rate for a player with no unlocker (an unlocker card itself at the higher rate)", () => {
    const r = recommend(profile([person()]), data(cards, [currency]));
    // lesser 100,000 x 1.0c = 1000; flat 1200; unlocker 60,000 x 1.5c = 900 (getting it unlocks the currency)
    expect(ids(r)).toEqual(["flat", "lesser", "unlocker"]);
  });

  it("values it at the higher rate once the player holds an unlocker", () => {
    const p = person("P1", {}, { unlocker: { current: 1, approved: { gt48: 1 } } });
    const r = recommend(profile([p]), data(cards, [currency]));
    // lesser 100,000 x 1.5c = 1500 beats flat 1200
    expect(ids(r).slice(0, 2)).toEqual(["lesser", "flat"]);
  });
});

describe("recommend: best personal cards", () => {
  const history = { h1: { approved: { lt12: 1 } }, h2: { approved: { lt12: 1 } }, h3: { approved: { lt12: 1 } }, h4: { approved: { lt12: 1 } } };
  const past = ["h1", "h2", "h3", "h4"].map((id) => mk(id, 0, { recommendable: false }));
  const cards = [
    ...past, mk("p1", 900), mk("p2", 800), mk("p3", 700), mk("p4", 600),
    mk("biz", 500, { kind: "business", reportsToPersonal: false }),
  ];

  it("hides cards that would count toward 5/24 from the main list and offers the top 3 personal cards separately", () => {
    const p = person("P1", { wantsUnder524: true }, history);
    const r = recommend(profile([p]), data(cards));
    expect(ids(r)).toEqual(["biz"]);
    expect(r.bestPersonal).toHaveLength(1);
    expect(r.bestPersonal[0]!.player).toBe("P1");
    expect(r.bestPersonal[0]!.cards.map((e) => e.cardId)).toEqual(["p1", "p2", "p3"]);
  });

  it("gives nothing extra to a player below 4/24 or one who does not care", () => {
    const relaxed = person("P1", { wantsUnder524: false }, history);
    expect(recommend(profile([relaxed]), data(cards)).bestPersonal).toEqual([]);
    const low = person("P1", { wantsUnder524: true }, { h1: history.h1 });
    expect(recommend(profile([low]), data(cards)).bestPersonal).toEqual([]);
  });
});

describe("recommend: real data", () => {
  const real: EngineData = {
    catalog: cardsJson as unknown as Card[], currencies: currenciesJson as unknown as Currency[],
    programs: programsJson as unknown as EngineData["programs"], valuations: valuationsJson as unknown as EngineData["valuations"],
    marriottMatrix: matrixJson as unknown as EngineData["marriottMatrix"],
  };
  const validate = new Ajv2020({ strict: false }).compile(resultsSchema);

  it("produces schema-valid results for a new player", () => {
    const r = recommend(profile([person()], { maxAnnualFee: 700, spend3Months: 8000, spend6Months: 16000 }), real);
    expect(validate(r), JSON.stringify(validate.errors)).toBe(true);
    expect(r.ranked.length).toBeGreaterThanOrEqual(5);
  });

  it("never lists a card that hardExclusion would hide, and lists at most 5 plus one backup per ceiling card", () => {
    const r = recommend(profile([person("Solo", { openToBusinessCards: false })], { maxAnnualFee: 700, spend3Months: 8000, spend6Months: 16000 }), real);
    const main = r.ranked.filter((e) => !e.players[0]!.backup);
    const backups = r.ranked.filter((e) => e.players[0]!.backup);
    expect(main).toHaveLength(5);
    expect(backups.length).toBeLessThanOrEqual(main.filter((e) => e.ceiling).length);
    for (const e of r.ranked) expect(real.catalog.find((c) => c.id === e.cardId)!.kind).toBe("personal");
  });

  it("is valid for two players, one with cards and one shut down by Chase", () => {
    const p1 = person("P1", {}, { "chase-sapphire-preferred": { current: 1, approved: { m12to24: 1 } } });
    const p2 = person("P2", { shutdownIssuers: ["chase"], wantsUnder524: true });
    const r = recommend(profile([p1, p2], { spend3Months: 6000, spend6Months: 12000 }), real);
    expect(validate(r), JSON.stringify(validate.errors)).toBe(true);
    for (const e of r.ranked) {
      const card = real.catalog.find((c) => c.id === e.cardId)!;
      if (card.issuer === "chase") expect(e.players.map((p) => p.name)).toEqual(["P1"]);
    }
  });
});
