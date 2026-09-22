import type { Card, CardHistoryEntry, MarriottMatrix, OtherPersonalCards, Player, Profile } from "../engine/types";

export const MAX_PLAYERS = 6;

/** Issuer sections of the card history step, in the order the design lists them (docs/questionnaire-design.md).
 * Synchrony and TD Bank deliberately have no section (owner, 2026-09-22): the catalog has no specific cards for
 * either, so a dedicated section would only ever show the free-entry "other cards" line anyway, with nothing to
 * distinguish it from just using the generic "Other issuers not listed" section already at the bottom of the
 * step. If either issuer ever gets real tracked cards, give it a section back then. */
export const ISSUER_SECTIONS = [
  { id: "chase", name: "Chase" },
  { id: "amex", name: "American Express" },
  { id: "boa", name: "Bank of America" },
  { id: "citi", name: "Citi" },
  { id: "usbank", name: "U.S. Bank" },
  { id: "wellsfargo", name: "Wells Fargo" },
  { id: "bilt", name: "Bilt" },
  { id: "barclays", name: "Barclays" },
  { id: "capone", name: "Capital One" },
  { id: "discover", name: "Discover" },
  { id: "fnbo", name: "FNBO" },
] as const;

// Amex-issued cards sold through a brokerage's own pages (schwab, morganstanley); shown under Amex, matching how
// historyCardsByIssuer already folds them into the Amex section of the card-history step.
const ISSUER_DISPLAY_FALLBACK: Record<string, string> = { schwab: "amex", morganstanley: "amex" };

/** A short display name for a card's issuer id (e.g. "capone" -> "Capital One"), for issuer badges in result lists. */
export function issuerLabel(issuer: string): string {
  const id = ISSUER_DISPLAY_FALLBACK[issuer] ?? issuer;
  return ISSUER_SECTIONS.find((s) => s.id === id)?.name ?? issuer;
}

export type CountField = "current" | "lt12" | "m12to24" | "m24to48" | "gt48";
export type MarriottFlag = "closedWithin30Days" | "approvedWithin90Days";

export function newPlayer(n: number): Player {
  return {
    name: `Player ${n}`,
    history: { cards: {}, otherPersonalByIssuer: {} },
    shutdownIssuers: [],
    bannedFromAA: false,
    openToBusinessCards: true,
    wantsUnder524: false,
    hasBoaDepositAccount: false,
    hasAmexBusinessChecking: false,
    willingToFormLlcForInk: false,
    showAmexNllCards: true,
  };
}

export function defaultProfile(players = 1): Profile {
  return {
    version: 1,
    players: Array.from({ length: players }, (_, i) => newPlayer(i + 1)),
    // Every spending answer starts genuinely blank (null), exactly like maxAnnualFee, shown as an empty box with
    // a suggested figure as its placeholder rather than a pre-filled guess (owner, 2026-09-22) — spend3Months is
    // the one the household must actually answer for the tool to produce anything useful; spend6Months, left
    // blank, is assumed to be double spend3Months (spendCapacity in householdFilters.ts).
    household: {
      maxAnnualFee: null, spend3Months: null, spend6Months: null, supplementalSpend3Months: null, bonusTypes: [],
      excludedPrograms: [], targetPrograms: [],
    },
  };
}

const whole = (n: number): number => (Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0);

/** A copy of the profile with one player replaced by `change(player)`. Never changes its input. */
function updatePlayer(profile: Profile, index: number, change: (p: Player) => Player): Profile {
  return { ...profile, players: profile.players.map((p, i) => (i === index ? change(p) : p)) };
}

export function setPlayerCount(profile: Profile, count: number): Profile {
  const n = Math.min(MAX_PLAYERS, Math.max(1, Math.floor(count)));
  const players = profile.players.slice(0, n);
  while (players.length < n) players.push(newPlayer(players.length + 1));
  return { ...profile, players };
}

/** Drops zero counts, and the entry itself when nothing is left. Returns undefined for an empty entry. */
function tidy(entry: CardHistoryEntry): CardHistoryEntry | undefined {
  const approved = Object.fromEntries(Object.entries(entry.approved ?? {}).filter(([, v]) => v > 0));
  const out: CardHistoryEntry = { current: entry.current ?? 0, approved };
  if (entry.marriott && Object.keys(entry.marriott).length > 0) out.marriott = entry.marriott;
  if ((out.current ?? 0) === 0 && Object.keys(approved).length === 0 && !out.marriott) return undefined;
  return out;
}

function withEntry(profile: Profile, index: number, cardId: string, entry: CardHistoryEntry | undefined): Profile {
  return updatePlayer(profile, index, (p) => {
    const cards = { ...(p.history.cards ?? {}) };
    if (entry) cards[cardId] = entry;
    else delete cards[cardId];
    return { ...p, history: { ...p.history, cards } };
  });
}

/**
 * Sets one count for a card: `current` (copies held now) or one approval window. Each field is independent
 * (owner, 2026-09-22) — setting one never changes `current` or any other window's value. An earlier version
 * tried to keep "current can't exceed total approved" as an invariant by auto-filling or clamping other fields,
 * which meant entering "hold now" silently wrote a 1 into "approved under 12 months ago", and correcting the
 * real approval window afterward left that guessed value behind instead of replacing it. The engine itself never
 * assumed that invariant either (computeDerived reads `current` and each `approved` window as independent
 * facts), so there was nothing downstream relying on it.
 */
export function setCardCount(profile: Profile, index: number, cardId: string, field: CountField, value: number): Profile {
  const v = whole(value);
  const existing = profile.players[index]?.history.cards?.[cardId];
  const entry: CardHistoryEntry = { ...existing, current: existing?.current ?? 0, approved: { ...(existing?.approved ?? {}) } };
  if (field === "current") entry.current = v;
  else entry.approved = { ...entry.approved, [field]: v };
  return withEntry(profile, index, cardId, tidy(entry));
}

/** Sets a Marriott-only answer (held within 30 days, approved within 90 days) for a card. */
export function setMarriottFlag(profile: Profile, index: number, cardId: string, flag: MarriottFlag, value: boolean): Profile {
  const existing = profile.players[index]?.history.cards?.[cardId];
  const marriott = { ...(existing?.marriott ?? {}) };
  if (value) marriott[flag] = true;
  else delete marriott[flag];
  const entry: CardHistoryEntry = { ...existing, current: existing?.current ?? 0, approved: { ...(existing?.approved ?? {}) }, marriott };
  return withEntry(profile, index, cardId, tidy(entry));
}

/** Sets a count in an "other [issuer] personal cards" line, or in the line for issuers not listed ("other"). */
export function setOtherCount(profile: Profile, index: number, issuer: string, field: "lt12" | "m12to24", value: number): Profile {
  const v = whole(value);
  const clean = (o: OtherPersonalCards): OtherPersonalCards => Object.fromEntries(Object.entries(o).filter(([, n]) => n > 0));
  return updatePlayer(profile, index, (p) => {
    if (issuer === "other") {
      const other = clean({ ...(p.history.otherIssuersPersonal ?? {}), [field]: v });
      const history = { ...p.history };
      if (Object.keys(other).length) history.otherIssuersPersonal = other;
      else delete history.otherIssuersPersonal;
      return { ...p, history };
    }
    const byIssuer = { ...(p.history.otherPersonalByIssuer ?? {}) };
    const line = clean({ ...(byIssuer[issuer] ?? {}), [field]: v });
    if (Object.keys(line).length) byIssuer[issuer] = line;
    else delete byIssuer[issuer];
    return { ...p, history: { ...p.history, otherPersonalByIssuer: byIssuer } };
  });
}

/**
 * Adds or removes a program from the household's excluded list or its target list. A program cannot be both, so choosing
 * it on one list removes it from the other.
 */
export function setProgramChoice(profile: Profile, list: "excluded" | "targeted", program: string, on: boolean): Profile {
  const excluded = profile.household.excludedPrograms.filter((p) => p !== program);
  const targeted = (profile.household.targetPrograms ?? []).filter((p) => p !== program);
  if (on) (list === "excluded" ? excluded : targeted).push(program);
  return { ...profile, household: { ...profile.household, excludedPrograms: excluded, targetPrograms: targeted } };
}

/** The "this player has no cards" shortcut: empties one player's card history. */
export function clearHistory(profile: Profile, index: number): Profile {
  return updatePlayer(profile, index, (p) => ({ ...p, history: { cards: {}, otherPersonalByIssuer: {} } }));
}

/** Reads a saved profile, or null if it is missing, damaged or from another version (the site then starts fresh). */
export function parseStoredProfile(raw: string | null): Profile | null {
  if (!raw) return null;
  try {
    const p = JSON.parse(raw) as Profile;
    const h = p.household;
    const ok =
      p.version === 1 && Array.isArray(p.players) && p.players.length >= 1 && p.players.length <= MAX_PLAYERS &&
      p.players.every((q) => typeof q.name === "string" && typeof q.history === "object" && q.history !== null && Array.isArray(q.shutdownIssuers)) &&
      typeof h === "object" && h !== null && (typeof h.maxAnnualFee === "number" || h.maxAnnualFee === null) && Array.isArray(h.bonusTypes) && Array.isArray(h.excludedPrograms);
    return ok ? p : null;
  } catch {
    return null;
  }
}

const SECTION_OF_ISSUER: Record<string, string> = { schwab: "amex", morganstanley: "amex" };

/**
 * The cards listed in each issuer section of the history step. A card is listed if it can be recommended, or if a rule
 * needs to know about it: a family, the Amex charge card limit, a business card that reports to personal credit, the
 * Marriott matrix, or another card's lifetime rule. Other personal cards go in the "other [issuer] cards" line.
 */
export function historyCardsByIssuer(catalog: Card[], matrix: MarriottMatrix): Map<string, Card[]> {
  const named = new Set<string>((matrix.cards ?? []).map((c) => c.id));
  for (const c of catalog) for (const id of c.bonusRules?.lifetimeAlsoBlockedBy ?? []) named.add(id);

  const sections = new Map<string, Card[]>(ISSUER_SECTIONS.map((s) => [s.id as string, []]));
  for (const c of catalog) {
    const listed =
      c.recommendable || c.family || c.bonusRules?.marriottMatrixKey || c.chargeCard || named.has(c.id) ||
      (c.kind === "business" && c.reportsToPersonal);
    if (!listed) continue;
    sections.get(SECTION_OF_ISSUER[c.issuer] ?? c.issuer)?.push(c);
  }
  for (const list of sections.values()) {
    list.sort((a, b) => (a.kind === b.kind ? a.name.localeCompare(b.name) : a.kind === "personal" ? -1 : 1));
  }
  return sections;
}
