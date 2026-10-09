// Types mirror data/schema/*.json. Only the fields the engine reads are listed.

export type Kind = "personal" | "business";

export interface Card {
  id: string;
  name: string;
  issuer: string;
  kind: Kind;
  recommendable: boolean;
  annualFee?: number;
  firstYearFeeWaived?: boolean;
  reportsToPersonal: boolean;
  chargeCard?: boolean;
  requiresAAAccess?: boolean;
  currency?: string;
  bonusTypes?: string[];
  unrankedReason?: string;
  welcomeBonus?: WelcomeBonus;
  coBrandedProgram?: string;
  typicalMinSpend?: { amount: number; months: number };
  family?: { id: string; tier: number };
  bonusRules?: BonusRules;
  sourceUrl?: string;
  /** Date the offer and fee were last checked against the issuer's page. */
  verifiedOn: string;
}

export interface BonusRules {
  onceInLifetime?: boolean;
  lifetimeAlsoBlockedBy?: string[];
  cooldownMonths?: number;
  cooldownBasis?: "bonus" | "held";
  cooldownFamily?: string;
  blockedWhileHeld?: boolean;
  marriottMatrixKey?: string;
}

export interface MarriottRule {
  heldWithinDays?: number;
  approvedWithinDays?: number;
  bonusWithinMonths?: number;
  blockedIfHeld?: boolean;
  ever?: boolean;
}

/** data/marriott-matrix.json: rules by code, and for each prior card the code that applies to each wanted card. */
export interface MarriottMatrix {
  /** The cards the matrix names (prior and wanted), for the history step. The engine does not read it. */
  cards?: { id: string; name: string; canBeWanted: boolean }[];
  rules: Record<string, MarriottRule>;
  matrix: Record<string, Record<string, string>>;
}

export interface ApprovalCounts {
  lt12?: number;
  m12to24?: number;
  m24to48?: number;
  gt48?: number;
}

export interface CardHistoryEntry {
  current?: number;
  approved?: ApprovalCounts;
  marriott?: { closedWithin30Days?: boolean; approvedWithin90Days?: boolean };
}

export interface OtherPersonalCards {
  lt12?: number;
  m12to24?: number;
}

export interface PlayerHistory {
  cards?: Record<string, CardHistoryEntry>;
  otherPersonalByIssuer?: Record<string, OtherPersonalCards>;
  otherIssuersPersonal?: OtherPersonalCards;
}

export interface Player {
  name: string;
  history: PlayerHistory;
  shutdownIssuers: string[];
  bannedFromAA: boolean;
  openToBusinessCards: boolean;
  wantsUnder524: boolean;
  hasBoaDepositAccount?: boolean;
  hasAmexBusinessChecking?: boolean;
  /**
   * Lives in a state where forming an LLC is free or cheap, and is willing to form one (with its own EIN, for a real
   * business) to get around Chase's Ink lifetime limit (K7). A "yes" lifts the lifetime block for every Ink card.
   */
  willingToFormLlcForInk?: boolean;
  /**
   * Whether to show Amex cards whose bonus would need a targeted "no lifetime language" (NLL) offer (owner,
   * 2026-09-22). Undefined means yes (the historical default: show them, flagged with the NLL note). A "no" hard-
   * excludes them instead of just flagging them — recommend.ts checks this, not hardExclusion.ts, since it needs
   * the same nllBlock() call recommend.ts already makes to compute the flag in the first place.
   */
  showAmexNllCards?: boolean;
}

export interface Derived {
  /** Personal-report cards approved in the last 24 months, plus other personal cards. Authorized-user accounts are ignored (owner, 2026-09-21). */
  x24: number;
  overFiveTwentyFour: boolean;
  /** Open Amex-issued credit cards (personal and business) and charge cards, for the 5 and 10 limits. */
  amexCredit: number;
  amexCharge: number;
  chaseBusinessOpen: number;
  /** Cards that report to personal credit opened in the last 12 months, including other personal cards. */
  x12: number;
  /** Copies currently held, and cards approved in the last 12 months, per issuer (all cards, business included). */
  currentByIssuer: Record<string, number>;
  approved12ByIssuer: Record<string, number>;
  /** Chase Ink cards currently held, split by whether the card has an annual fee (one of each is allowed). */
  inkNoFee: number;
  inkAnnualFee: number;
  /** Every catalog card the player has ever been approved for (currently held or any approval count above 0). */
  everHad: Set<string>;
  /** History entries whose card id is not in the catalog (for example a card removed since the profile was saved). */
  unknownCardIds: string[];
}

export interface Currency {
  id: string;
  name?: string;
  /** Cards that unlock transfers to partners when held. Empty means transfers need no unlocking card. */
  unlockerCards: string[];
  /** Program ids this currency transfers to. */
  partners: string[];
  /** How good a cash-out is: 'good', 'poor' or 'none'. */
  cashBackRedemption: "good" | "poor" | "none";
  /** For a "poor" cash-out: combinations that make it good for a player (cards held now, plus an account if named). */
  cashBackQualifiers?: { cards: string[]; account?: "amexBusinessChecking" }[];
  /** True if one household member's unlocker counts for the others. */
  householdPooling: boolean;
}

export interface Program {
  id: string;
  name: string;
  kind: "airline" | "hotel";
  /** Programs that are one loyalty currency under several names (the Avios airlines) share a group. */
  group?: string;
}

export interface Household {
  /** Highest annual fee accepted on a single card in its first year (a waived first year counts as $0). Null means no limit. */
  maxAnnualFee: number | null;
  /** Null means not answered yet; spendCapacity() treats it as 0 (nothing is reachable until this is answered). */
  spend3Months: number | null;
  /** Null means not answered; spendCapacity() then assumes double spend3Months, since a real 6-month total lower
   * than the 3-month total is never a sensible answer (spend only grows over time). */
  spend6Months: number | null;
  supplementalSpend3Months: number | null;
  bonusTypes: string[];
  excludedPrograms: string[];
  /** Programs the household is planning a redemption in. Cards that lead to them are ranked above the rest. */
  targetPrograms?: string[];
}

export type ExclusionKind =
  | "notRecommendable"
  | "shutdown"
  | "aaBan"
  | "businessNotWanted"
  | "annualFee"
  | "spend"
  | "excludedProgram"
  | "unranked"
  | "noWantedBonusType"
  | "noUnlocker"
  | "chase5_24"
  | "ink3_24"
  | "barclays6_24"
  | "usbank5_12"
  | "amexCardLimits"
  | "boaCardCount"
  | "discoverLimits"
  | "inkLimit"
  | "stayUnder524"
  | "lifetime"
  | "family"
  | "cooldown"
  | "marriottMatrix";

/** Why a card is hidden for a player. The UI does not show the reason; tests and debugging do. */
export interface Exclusion {
  kind: ExclusionKind;
  reason: string;
}

export interface BonusTier {
  points?: number;
  cashBack?: number;
  minSpend?: number;
  windowMonths?: number;
  /** What minSpend means: "more" (on top of the first tier's spend, the default), "total" (cumulative since opening,
   * already including the first tier's spend) or "merchant" (spend at the named merchant). */
  spendBasis?: "more" | "total" | "merchant";
  merchant?: string;
}

export interface WelcomeBonus {
  points?: number;
  cashBack?: number;
  /** Dollar figure shown when the issuer advertises points as cash back; the value comes from `points`. */
  displayedAsCash?: number;
  /** Dollar value of free night certificates and other components (from valuations.json when the catalog was built). */
  otherValue?: number;
  /** Number of free night certificates in the bonus (for display; their dollar value is in otherValue). */
  freeNights?: number;
  additionalTiers?: BonusTier[];
  /** An "as high as" ceiling (Amex), not a fixed offer. */
  ceiling?: boolean;
}

/** data/valuations.json: cents per point per currency, one rate or two for currencies that need an unlocking card. */
export interface Valuations {
  values: Record<string, number | { withUnlocker: number; withoutUnlocker: number }>;
  freeNightCertificates: Record<string, number>;
  /** Date these point values were last checked against the source (Frequent Miler's RRVs). */
  verifiedOn?: string;
}

export interface Profile {
  version: 1;
  players: Player[];
  household: Household;
}

/** Everything the engine reads besides the profile. */
export interface EngineData {
  catalog: Card[];
  currencies: Currency[];
  programs: Program[];
  valuations: Valuations;
  marriottMatrix: MarriottMatrix;
}

export interface ResultPlayerStanding {
  name: string;
  x24: number;
  overFiveTwentyFour: boolean;
  amexCredit: number;
  amexCharge: number;
  chaseBusinessOpen: number;
}

export interface ResultEntry {
  cardId: string;
  players: { name: string; viaNllOnly?: boolean; backup?: boolean }[];
  annualFee: number;
  firstYearFeeWaived?: boolean;
  minSpend?: { amount: number; months: number };
  ceiling?: boolean;
  /** Dollar value of the welcome bonus, and that value minus the first-year annual fee (the highest any listed player gets). */
  bonusValue: number;
  netValue: number;
}

/** data/schema/results.schema.json */
export interface Results {
  players: ResultPlayerStanding[];
  ranked: ResultEntry[];
  bestPersonal: { player: string; cards: ResultEntry[] }[];
}
