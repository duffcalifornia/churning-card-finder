import { describe, expect, it } from "vitest";
import { groupChangelog, parseChangelogEntries } from "./changelogGroups";

const SAMPLE = `Intro line, not a heading.

## 2028-04-15
- April thing two

## 2028-04-02
- April thing one

## 2028-03-10
- March thing

## 2028-01-05
- January thing

## 2027-12-20
- December 2027 thing

## 2027-06-01
- June 2027 thing

## 2026-11-30
- November 2026 thing
`;

describe("parseChangelogEntries", () => {
  it("splits every heading into its own entry, in source order", () => {
    const entries = parseChangelogEntries(SAMPLE);
    expect(entries.map((e) => e.date)).toEqual([
      "2028-04-15", "2028-04-02", "2028-03-10", "2028-01-05", "2027-12-20", "2027-06-01", "2026-11-30",
    ]);
  });

  it("parses the date into year and a 0-indexed month", () => {
    const [first] = parseChangelogEntries(SAMPLE);
    expect(first).toMatchObject({ year: 2028, month: 3 }); // April = index 3
  });

  it("parses each entry's body as markdown", () => {
    const [first] = parseChangelogEntries(SAMPLE);
    expect(first!.html).toContain("<li>April thing two</li>");
  });
});

describe("groupChangelog", () => {
  const entries = parseChangelogEntries(SAMPLE);
  const now = new Date("2028-04-20");

  it("puts every entry from the current month in currentMonthEntries, newest first", () => {
    const { currentMonthEntries } = groupChangelog(entries, now);
    expect(currentMonthEntries.map((e) => e.date)).toEqual(["2028-04-15", "2028-04-02"]);
  });

  it("groups the rest of the current year by month, newest month first", () => {
    const { sameYearMonths } = groupChangelog(entries, now);
    expect(sameYearMonths.map((g) => g.month)).toEqual([2, 0]); // March, January
    expect(sameYearMonths[0]!.entries.map((e) => e.date)).toEqual(["2028-03-10"]);
  });

  it("groups past years newest first, each with its own months newest first", () => {
    const { pastYears } = groupChangelog(entries, now);
    expect(pastYears.map((y) => y.year)).toEqual([2027, 2026]);
    expect(pastYears[0]!.months.map((m) => m.month)).toEqual([11, 5]); // December, June
    expect(pastYears[1]!.months.map((m) => m.month)).toEqual([10]); // November
  });

  it("has no entries left over: every entry lands in exactly one bucket", () => {
    const { currentMonthEntries, sameYearMonths, pastYears } = groupChangelog(entries, now);
    const total = currentMonthEntries.length
      + sameYearMonths.reduce((n, g) => n + g.entries.length, 0)
      + pastYears.reduce((n, y) => n + y.months.reduce((m, g) => m + g.entries.length, 0), 0);
    expect(total).toBe(entries.length);
  });
});
