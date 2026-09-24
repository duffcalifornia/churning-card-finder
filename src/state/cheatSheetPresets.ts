import { recommend, type RankBy } from "../engine/recommend";
import type { EngineData, Household, Player, Profile, ResultEntry } from "../engine/types";

export type FiveTwentyFourStatus = "under" | "over";
export type BonusFocus = "cashback" | "travel";

export interface CheatSheetPreset {
  id: string;
  label: string;
  fiveTwentyFour: FiveTwentyFourStatus;
  focus: BonusFocus;
}

/**
 * The Signup Offer Cheat Sheet's four columns: a fast, no-questions reference for someone who already knows their
 * own real 5/24 status and history and just wants the generic "best right now" answer for their situation, not a
 * personalized recommendation. Deliberately not a fifth "mixed" option — the flowchart this replaces is exactly
 * these four boxes.
 */
export const CHEAT_SHEET_PRESETS: CheatSheetPreset[] = [
  { id: "under-cashback", label: "Under 5/24, cash back", fiveTwentyFour: "under", focus: "cashback" },
  { id: "under-travel", label: "Under 5/24, travel", fiveTwentyFour: "under", focus: "travel" },
  { id: "over-cashback", label: "5/24 or over, cash back", fiveTwentyFour: "over", focus: "cashback" },
  { id: "over-travel", label: "5/24 or over, travel", fiveTwentyFour: "over", focus: "travel" },
];

// Large but finite, not Infinity: spendCapacity()'s interpolation does real arithmetic on these (at6 - at3), and
// Infinity - Infinity is NaN. No real card's minimum spend approaches this, so the spend filter never fires.
const UNLIMITED_SPEND = 1_000_000;

/**
 * The hypothetical profile behind one column: never held any of these cards (so no lifetime, family, cooldown or
 * Marriott block can fire), can spend anything (so the minimum-spend filter never fires), and no annual fee limit.
 * The only two things that vary are 5/24 status and the wanted bonus type — the two axes of the original flowchart.
 *
 * "Over 5/24" is simulated with 5 generic personal cards in the 12-to-24-month bucket, not the under-12 one: that
 * trips only the 24-month rules (Chase 5/24, and Ink's stricter 3/24) without also tripping BoA's or US Bank's
 * unrelated 12-month velocity rules as an unintended side effect of faking a history.
 */
export function presetProfile(preset: CheatSheetPreset): Profile {
  const player: Player = {
    name: "Hypothetical",
    history: {
      cards: {},
      otherIssuersPersonal: preset.fiveTwentyFour === "over" ? { m12to24: 5 } : {},
    },
    shutdownIssuers: [],
    bannedFromAA: false,
    openToBusinessCards: true,
    wantsUnder524: false, // show everything directly; this page has no "Best Personal Cards" side list
  };
  const household: Household = {
    maxAnnualFee: null,
    spend3Months: UNLIMITED_SPEND,
    spend6Months: UNLIMITED_SPEND * 2,
    supplementalSpend3Months: 0,
    bonusTypes: preset.focus === "cashback" ? ["cashback"] : ["hotel", "airline"],
    excludedPrograms: [],
  };
  return { version: 1, players: [player], household };
}

/** Every eligible card for this preset, ranked, with nothing held back to a top N: this page is a full reference. */
export function rankForPreset(preset: CheatSheetPreset, data: EngineData, rankBy: RankBy): ResultEntry[] {
  // On the cash-back columns, Ultimate Rewards' own unlocker cards (Sapphire Preferred/Reserve, Ink Preferred)
  // would otherwise still be valued at the travel-transfer rate, since getting one of them unlocks the currency -
  // but a page about cashing out shouldn't show a card's travel value. Non-unlocker UR earners are unaffected:
  // this hypothetical player holds nothing, so they already price at the cash rate. Amex Membership Rewards is
  // deliberately left alone: its cash-out is only good with specific cards/accounts (Schwab Platinum, or Business
  // Platinum plus an Amex Business Checking account) that this no-history hypothetical can never model either way.
  const forceCashOutCurrencies = preset.focus === "cashback" ? ["ultimate-rewards"] : undefined;
  return recommend(presetProfile(preset), data, { perPlayer: Number.POSITIVE_INFINITY, rankBy, forceCashOutCurrencies }).ranked;
}
