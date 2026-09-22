import { describe, expect, it } from "vitest";
import { unlockStatus } from "./unlockStatus";
import type { Card, Currency, Player, PlayerHistory } from "./types";
import cardsJson from "../../data/cards.json";
import currenciesJson from "../../data/currencies.json";

const player = (name: string, cards: PlayerHistory["cards"] = {}): Player => ({
  name, history: { cards }, shutdownIssuers: [], bannedFromAA: false, openToBusinessCards: true, wantsUnder524: false,
});
const held = (n = 1) => ({ current: n, approved: { lt12: n } });

const CURRENCIES: Currency[] = [
  { id: "pooled", unlockerCards: ["key-a", "key-b"], householdPooling: true, partners: [], cashBackRedemption: "good" },
  { id: "solo", unlockerCards: ["key-c"], householdPooling: false, partners: [], cashBackRedemption: "good" },
  { id: "open", unlockerCards: [], householdPooling: false, partners: [], cashBackRedemption: "good" },
];

describe("unlockStatus", () => {
  it("lists every currency for every player", () => {
    const r = unlockStatus([player("A"), player("B")], CURRENCIES);
    expect([...r.keys()]).toEqual(["A", "B"]);
    expect([...r.get("A")!.keys()]).toEqual(["pooled", "solo", "open"]);
  });

  it("is unlocked with an unlocker card held, and locked without one", () => {
    const r = unlockStatus([player("A", { "key-a": held() })], CURRENCIES);
    expect(r.get("A")!.get("pooled")).toBe(true);
    expect(r.get("A")!.get("solo")).toBe(false);
  });

  it("accepts any of a currency's unlocker cards", () => {
    const r = unlockStatus([player("A", { "key-b": held() })], CURRENCIES);
    expect(r.get("A")!.get("pooled")).toBe(true);
  });

  it("needs no unlocker for a currency that has none", () => {
    const r = unlockStatus([player("A")], CURRENCIES);
    expect(r.get("A")!.get("open")).toBe(true);
  });

  it("does not count a card the player only used to hold", () => {
    const closed = { current: 0, approved: { gt48: 1 } };
    const r = unlockStatus([player("A", { "key-a": closed })], CURRENCIES);
    expect(r.get("A")!.get("pooled")).toBe(false);
  });

  it("pools an unlocker across the household when the currency allows it", () => {
    const r = unlockStatus([player("A", { "key-a": held() }), player("B")], CURRENCIES);
    expect(r.get("B")!.get("pooled")).toBe(true);
  });

  it("keeps an unlocker with its holder when the currency does not pool", () => {
    const r = unlockStatus([player("A", { "key-c": held() }), player("B")], CURRENCIES);
    expect(r.get("A")!.get("solo")).toBe(true);
    expect(r.get("B")!.get("solo")).toBe(false);
  });

  it("handles a single player", () => {
    const r = unlockStatus([player("Solo", { "key-c": held(2) })], CURRENCIES);
    expect(r.get("Solo")!.get("solo")).toBe(true);
  });

  it("rejects two players with the same name", () => {
    expect(() => unlockStatus([player("A"), player("A")], CURRENCIES)).toThrow(/same name/);
  });

  it("does not change its input", () => {
    const players = [player("A", { "key-a": held() })];
    const before = JSON.stringify(players);
    unlockStatus(players, CURRENCIES);
    expect(JSON.stringify(players)).toBe(before);
  });
});

describe("unlockStatus: real currency data", () => {
  const currencies = currenciesJson as unknown as Currency[];
  const catalogIds = new Set((cardsJson as unknown as Card[]).map((c) => c.id));

  it("names only cards that exist in the catalog", () => {
    for (const c of currencies) for (const id of c.unlockerCards) expect(catalogIds.has(id), id).toBe(true);
  });

  it("follows the owner's rules for Chase, Citi, Capital One and Amex", () => {
    const r = unlockStatus([
      player("Saph", { "chase-sapphire-preferred": held() }),
      player("Strata", { "citi-strata-premier": held() }),
      player("Plain"),
    ], currencies);
    // Chase and Capital One points pool; Citi and Amex do not (Amex needs no unlocker at all)
    expect(r.get("Plain")!.get("ultimate-rewards")).toBe(true);
    expect(r.get("Strata")!.get("ultimate-rewards")).toBe(true);
    expect(r.get("Saph")!.get("citi-thankyou")).toBe(false);
    expect(r.get("Strata")!.get("citi-thankyou")).toBe(true);
    expect(r.get("Plain")!.get("citi-thankyou")).toBe(false);
    expect(r.get("Plain")!.get("amex-membership-rewards")).toBe(true);
    expect(r.get("Plain")!.get("capital-one-miles")).toBe(false);
  });

  it("counts Ink Preferred and the business Sapphire Reserve for Chase, and Venture X Business for Capital One", () => {
    const ink = unlockStatus([player("A", { "chase-ink-preferred": held() })], currencies);
    expect(ink.get("A")!.get("ultimate-rewards")).toBe(true);
    const biz = unlockStatus([player("A", { "chase-sapphire-reserve-business": held() })], currencies);
    expect(biz.get("A")!.get("ultimate-rewards")).toBe(true);
    const cap = unlockStatus([player("A"), player("B", { "capone-venture-x-business": held() })], currencies);
    expect(cap.get("A")!.get("capital-one-miles")).toBe(true);
  });

  it("does not let Ink Cash or Ink Unlimited unlock Ultimate Rewards", () => {
    const r = unlockStatus([player("A", { "chase-ink-cash": held(), "chase-freedom-unlimited": held() })], currencies);
    expect(r.get("A")!.get("ultimate-rewards")).toBe(false);
  });
});
