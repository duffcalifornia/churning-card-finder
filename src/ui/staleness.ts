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
