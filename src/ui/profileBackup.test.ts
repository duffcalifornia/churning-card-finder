import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { describeElapsedSince } from "./profileBackup";

describe("describeElapsedSince", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-25T12:00:00Z"));
  });
  afterEach(() => vi.useRealTimers());

  it("returns null with no date at all", () => {
    expect(describeElapsedSince(undefined)).toBeNull();
  });

  it("returns null for an unparseable date", () => {
    expect(describeElapsedSince("not a date")).toBeNull();
  });

  it("treats today, and anything in the current calendar month, as 'less than a month ago'", () => {
    expect(describeElapsedSince("2026-09-25")).toBe("less than a month ago");
    expect(describeElapsedSince("2026-09-01")).toBe("less than a month ago");
  });

  it("says 'about 1 month ago' for a date a full calendar month back", () => {
    expect(describeElapsedSince("2026-08-25")).toBe("about 1 month ago");
  });

  it("says 'about N months ago' for anything further back", () => {
    expect(describeElapsedSince("2026-04-25")).toBe("about 5 months ago");
    expect(describeElapsedSince("2022-09-25")).toBe("about 48 months ago");
  });

  it("does not round up early: one day short of a full month still counts the earlier month", () => {
    // 2026-08-26 is one day short of a full calendar month before 2026-09-25.
    expect(describeElapsedSince("2026-08-26")).toBe("less than a month ago");
  });
});
