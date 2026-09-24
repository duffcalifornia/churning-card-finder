import { marked } from "marked";

export interface ChangelogEntry {
  date: string; // "2026-09-23"
  year: number;
  month: number; // 0-11
  html: string;
}

export interface MonthGroup {
  month: number; // 0-11
  entries: ChangelogEntry[];
}

export interface YearGroup {
  year: number;
  months: MonthGroup[];
}

export interface ChangelogGroups {
  currentMonthEntries: ChangelogEntry[];
  sameYearMonths: MonthGroup[];
  pastYears: YearGroup[];
}

const HEADING = /^## (\d{4}-\d{2}-\d{2})\s*$/gm;

/** Splits CHANGELOG.md's flat, newest-first `## YYYY-MM-DD` sections into individual entries, each with its
 * bullet list parsed to HTML. Safe to render as HTML: the source is CHANGELOG.md, a file only the maintainer
 * edits, never user input. */
export function parseChangelogEntries(md: string): ChangelogEntry[] {
  const headings: { date: string; start: number; bodyStart: number }[] = [];
  HEADING.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = HEADING.exec(md))) {
    headings.push({ date: m[1]!, start: m.index, bodyStart: m.index + m[0].length });
  }
  return headings.map((h, i) => {
    const end = i + 1 < headings.length ? headings[i + 1]!.start : md.length;
    const body = md.slice(h.bodyStart, end).trim();
    const [year, month] = h.date.split("-").map(Number);
    return { date: h.date, year: year!, month: month! - 1, html: marked.parse(body, { async: false }) as string };
  });
}

function groupByMonth(entries: ChangelogEntry[]): MonthGroup[] {
  const byMonth = new Map<number, ChangelogEntry[]>();
  for (const e of entries) {
    const list = byMonth.get(e.month);
    if (list) list.push(e);
    else byMonth.set(e.month, [e]);
  }
  return Array.from(byMonth.entries())
    .sort((a, b) => b[0] - a[0])
    .map(([month, monthEntries]) => ({ month, entries: monthEntries }));
}

/**
 * Groups changelog entries for display: the current month's entries stand alone and stay fully visible, every
 * other month of the current year gets its own collapsible group, and every earlier year collapses into one
 * group that itself contains that year's months as nested groups. No matter how long the changelog gets, this
 * stays a flat, one-line-per-group table of contents down to whichever specific month someone actually wants -
 * unlike collapsing a whole past year into a single undifferentiated block of entries, which would just move
 * the "wall of text" problem behind one extra click instead of solving it.
 */
export function groupChangelog(entries: ChangelogEntry[], now: Date): ChangelogGroups {
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth();

  const currentMonthEntries = entries.filter((e) => e.year === currentYear && e.month === currentMonth);
  const sameYearMonths = groupByMonth(entries.filter((e) => e.year === currentYear && e.month !== currentMonth));

  const byYear = new Map<number, ChangelogEntry[]>();
  for (const e of entries) {
    if (e.year >= currentYear) continue;
    const list = byYear.get(e.year);
    if (list) list.push(e);
    else byYear.set(e.year, [e]);
  }
  const pastYears = Array.from(byYear.entries())
    .sort((a, b) => b[0] - a[0])
    .map(([year, yearEntries]) => ({ year, months: groupByMonth(yearEntries) }));

  return { currentMonthEntries, sameYearMonths, pastYears };
}
