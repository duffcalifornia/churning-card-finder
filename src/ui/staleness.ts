import type { Card } from "../engine/types";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/**
 * A YYYY-MM-DD date as plain language ("September 20, 2026"). Parses the string's own year/month/day directly
 * rather than through `new Date(iso)`, which reads a date-only ISO string as UTC midnight and can print the wrong
 * day once formatted in a timezone west of UTC.
 */
export function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  return `${MONTHS[(month ?? 1) - 1]} ${day}, ${year}`;
}

/**
 * The earliest `verifiedOn` among cards actually shown in the ranking (recommendable, and not `unrankedReason`).
 * The honest "how fresh is this" figure is the oldest one still on screen, not the newest: showing the newest would
 * overstate how current the whole list is. Null if nothing is currently ranked.
 */
export function oldestVerifiedOn(catalog: Card[]): string | null {
  const dates = catalog.filter((c) => c.recommendable && !c.unrankedReason).map((c) => c.verifiedOn);
  return dates.length ? dates.reduce((a, b) => (a < b ? a : b)) : null;
}

export interface Freshness {
  /** The oldest review date among the cards that are current, or null if nothing is ranked. */
  current: string | null;
  /** Issuers whose ranked cards were last reviewed well before the rest (for example one the automated refresh skips). */
  older: { issuer: string; date: string }[];
}

const DAY_MS = 86_400_000;
const utcDay = (iso: string) => Date.UTC(...(iso.split("-").map(Number) as [number, number, number]).map((v, i) => (i === 1 ? v - 1 : v)) as [number, number, number]);

/**
 * How fresh the ranked cards are, without letting one stale issuer drag the headline date back: cards reviewed
 * within `graceDays` of the newest review count as current, and the headline is the oldest of those. Any issuer
 * whose cards are all older than that is listed separately with its own date, so nothing is hidden.
 */
export function freshness(catalog: Card[], graceDays = 3): Freshness {
  const ranked = catalog.filter((c) => c.recommendable && !c.unrankedReason);
  if (ranked.length === 0) return { current: null, older: [] };
  const newest = ranked.reduce((a, c) => (c.verifiedOn > a ? c.verifiedOn : a), ranked[0]!.verifiedOn);
  const isCurrent = (c: Card) => utcDay(newest) - utcDay(c.verifiedOn) <= graceDays * DAY_MS;
  const current = ranked.filter(isCurrent).reduce((a, c) => (c.verifiedOn < a ? c.verifiedOn : a), newest);
  const olderByIssuer = new Map<string, string>();
  for (const c of ranked.filter((c) => !isCurrent(c))) {
    const seen = olderByIssuer.get(c.issuer);
    if (seen === undefined || c.verifiedOn < seen) olderByIssuer.set(c.issuer, c.verifiedOn);
  }
  return { current, older: [...olderByIssuer].map(([issuer, date]) => ({ issuer, date })).sort((a, b) => a.date.localeCompare(b.date)) };
}
